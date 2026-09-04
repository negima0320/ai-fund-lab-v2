# Phase32-ER — Long-Lived Historical Penalty & Security-Level Bias Exhaustive Read-Only Audit

## Scope

- Target run: `runtime-test-historical-extended-smoke-20260902T060955933565Z`
- Evidence window inspected: run artifacts through `2024-12-20` where available.
- Source baseline recorded by the run: `source_commit=1f64f49ee9a8dd48280007e4df656e5f03e231ca`.
- This audit used decision-time/PIT artifacts only for Production correctness judgment.
- Production changed: NO.
- SHADOW changed: NO.
- Target run mutated: NO.
- Runtime state mutated: NO.
- Future outcome used for Production judgment: NO.

Primary references used:

- `docs/phase_reports/phase32_eq_long_run_state_history_accumulation_dependency_capital_suppression_root_cause_audit.md`
- `docs/phase_reports/phase32_eo_2023_strong_growth_vs_2024_post_march_stagnation_decision_time_characterization_audit.md`
- `docs/phase_reports/phase32_ep_next_capital_unit_opportunity_evidence_shadow_audit.md`
- `docs/phase_reports/phase32_en_bq_positive_pc_target_zero_boundary_shadow_audit.md`
- `docs/phase_reports/phase32_em_post_march_2024_candidate_selection_capitalization_funnel_pit_correctness_read_only_audit.md`
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- `src/ai_fund_lab_v2/strategy/position_management.py`
- `src/ai_fund_lab_v2/strategy/shadow_runtime.py`
- Target run daily `strategy/portfolio_construction.json`, `strategy/position_management.json`, `strategy/buy_quality_decisions.json`, `strategy/runtime_planning.json`, and PM/runtime evidence where present.

## Executive Finding

ER confirms a real long-lived security-level REENTRY penalty path.

The most important boundary is not short-term cooldown. Cooldown is bounded. The problematic path is:

`strict-prior ledger/campaign/PM history`
-> `symbol-level latest prior closed campaign`
-> `REENTRY semantic classification`
-> `Portfolio Construction target zero / non-capitalization`

When prior EXIT context is unknown, recoverable-but-not-materialized, or tied to old hard-stop/trend/profit-retention classifications, Production can continue to treat a symbol as REENTRY-risky for hundreds of business days. Current PIT evidence can release some cases, but unknown prior context and repeated unresolved churn can remain long-lived without a pure time release or new-equivalent reset.

No closed-campaign ADD/REDUCE history leakage was proven. ADD/REDUCE history gates found in PM are current-open-campaign scoped and are valid current-campaign controls in the inspected source/artifacts.

## REENTRY Suppression Age Buckets

Total REENTRY-suppressed rows extracted: `8002`.

| business_days_since_exit | rows | cooldown | repeated churn | trend recovery | momentum/recovery | new thesis | unknown context | other |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `<=10` | 2380 | 930 / 39.1% | 291 / 12.2% | 483 / 20.3% | 53 / 2.2% | 319 / 13.4% | 304 / 12.8% | 0 |
| `11-30` | 1094 | 0 | 300 / 27.4% | 239 / 21.8% | 59 / 5.4% | 249 / 22.8% | 246 / 22.5% | 1 |
| `31-60` | 778 | 0 | 263 / 33.8% | 151 / 19.4% | 34 / 4.4% | 125 / 16.1% | 205 / 26.3% | 0 |
| `61-120` | 924 | 0 | 349 / 37.8% | 119 / 12.9% | 22 / 2.4% | 165 / 17.9% | 269 / 29.1% | 0 |
| `121-250` | 1474 | 0 | 414 / 28.1% | 309 / 21.0% | 32 / 2.2% | 260 / 17.6% | 456 / 30.9% | 3 |
| `251-400` | 935 | 0 | 142 / 15.2% | 202 / 21.6% | 16 / 1.7% | 113 / 12.1% | 452 / 48.3% | 10 |
| `>400` | 417 | 0 | 18 / 4.3% | 88 / 21.1% | 11 / 2.6% | 126 / 30.2% | 170 / 40.8% | 4 |

The distribution shows that after the explicit cooldown window, suppression does not disappear. It shifts into current-evidence-dependent recovery failures and unknown-context/repeated-churn states. Unknown context is especially persistent: `170` cases remain beyond `400` business days since EXIT.

## Reason Release Classification

| reason family | time alone releases? | current PIT can release? | missing campaign/context can trap? | old campaign referenced? | symbol/campaign conflation risk | classification |
|---|---|---|---|---|---|---|
| cooldown | YES | not required | NO | latest prior EXIT only for age | LOW | `BOUNDED_VALID` |
| trend recovery not satisfied | NO | YES, if trend/momentum recover per contract | NO, unless coupled with unknown context | YES | MEDIUM | `AGE_UNBOUNDED_BUT_RECOVERABLE` |
| momentum/recovery failure | NO | YES | NO, unless coupled with unknown context | YES | MEDIUM | `CURRENT_EVIDENCE_DEPENDENT` |
| hard-stop new thesis not sufficient | NO | YES, but stricter FULL-quality/current-evidence requirements apply | possible | YES | MEDIUM | `AGE_UNBOUNDED_BUT_RECOVERABLE` |
| unknown prior context | NO | only if strong current evidence establishes independence; otherwise REVIEW_REQUIRED | YES | YES | HIGH | `UNKNOWN_CONTEXT_LONG_LIVED` / `POSSIBLE_EFFECTIVE_PERMANENT_PENALTY` |
| repeated unresolved churn | NO | sometimes, but requires all recovery gates to clear | YES when unknown context participates | YES | HIGH | `POSSIBLE_EFFECTIVE_PERMANENT_PENALTY` |

Aggregate reason classification:

- `BOUNDED_VALID`: `930`
- `CURRENT_EVIDENCE_DEPENDENT`: `18`
- `AGE_UNBOUNDED_BUT_RECOVERABLE`: `3175`
- `UNKNOWN_CONTEXT_LONG_LIVED`: `2102`
- `POSSIBLE_EFFECTIVE_PERMANENT_PENALTY`: `1777`

## EXIT Reason Impact On Future REENTRY

For 2024-07-01 through 2024-12-20 suppressed REENTRY rows, prior EXIT reasons were still active at long ages:

| prior EXIT reason | rows | average age | max age | current effect |
|---|---:|---:|---:|---|
| `strategy_intelligence_sell_side_evidence_connected` | 890 | 207.5 | 559 | often maps to old thesis/weak-hold context, then requires renewed evidence |
| `hard_stop_current_return` | 762 | 191.3 | 577 | triggers stricter hard-stop new-thesis recovery |
| `profit_retention_break` | 345 | 164.2 | 543 | can keep prior EXIT semantic context alive |
| `pm_discrete_control_persistent_deterioration_exit` | 146 | 85.8 | 398 | trend/deterioration recovery dependent |
| `peak_drawdown_warning` | 113 | 199.3 | 418 | risk/profit-protection prior context remains relevant |
| generic `EXIT` | 84 | 43.6 | 104 | shorter-lived in this sample |

Judgment: old EXIT reason can cause a long-lived block when it feeds technical recovery, hard-stop new-thesis, or unknown prior-context gates. The issue is not that old EXIT reason is referenced at all. The issue is that there is no bounded relevance contract separating a still-relevant recent failure from a stale symbol-level historical penalty.

## Production History Gates Enumerated

| area | history dependency found | suppresses capital? | expiry/release | ER judgment |
|---|---|---|---|---|
| candidate generation / shadow runtime | strict-prior ledger executions, prior closed campaigns by symbol, prior PM EXIT evidence | YES, by classifying same symbol as REENTRY and attaching prior context | no age expiry found; latest strict-prior closed campaign selected | `WHOLE_RUN_ACCUMULATION_BIAS` |
| BQ / buy quality | current PIT quality/rank/action; no direct prior ownership penalty proven | not directly | current evidence | `NOT_A_DEFECT` |
| Entry | entry caution/wait/reject fields can participate in REENTRY recovery failures | YES, when REENTRY path consumes entry block | current PIT can release | `VALID_CURRENT_EVIDENCE_DEPENDENCY` |
| PC REENTRY semantic gate | cooldown, prior context, recovery, safety, current eligibility | YES, target zero/non-capitalization | cooldown bounded; other gates age-unbounded | `LONG_LIVED_BUT_RELEASABLE_HISTORY_EFFECT` plus unknown-context defect candidate |
| PM current holdings | current campaign lifecycle, add/reduce/sell history | YES for ADD worthiness | current open campaign only | `VALID_CURRENT_CAMPAIGN_HISTORY` |
| ADD worthiness | `prior_add_history_limits_incremental_add` at add count >=5; `prior_reduce_history_requires_add_review` if reduce count >0 | YES for ADD | current campaign reset on new BUY_NEW/REENTRY campaign | `VALID_CURRENT_CAMPAIGN_HISTORY` |
| REDUCE/EXIT PM | current campaign returns, giveback, PM decision history | YES, via current holding action | current open campaign | `VALID_CURRENT_CAMPAIGN_HISTORY` |
| Runtime adapter/planning | campaign/provenance/idempotency/Pending identity | can block invalid orders, not security bias | per Pending/order lifecycle | `NOT_A_DEFECT` |
| Execution planning | idempotency/order-state history | no security-level bias found | order lifecycle bounded | `NOT_A_DEFECT` |
| Risk pacing | market/regime/equity/exposure state | portfolio-level only | current-day PIT/portfolio state | `NOT_A_DEFECT` |
| campaign materialization | latest prior campaign snapshot plus full strict-prior ledger/PM evidence scans | indirectly, because REENTRY context grows with run age | no bounded index/expiry found | `WHOLE_RUN_ACCUMULATION_BIAS` and performance-scaling concern |

## ADD / REDUCE History Leakage Audit

Source inspection:

- `position_management._structured_add_worthiness_evidence` uses `lifecycle.add_history_summary` and `lifecycle.reduce_history_summary`.
- `shadow_runtime._new_campaign_from_execution` starts a new campaign on BUY when prior quantity is zero.
- `shadow_runtime._merge_strict_prior_ledger_history_into_open_campaign` only merges ledger events that prove the same open campaign identity.
- ADD history increments only when BUY occurs while quantity is already positive.
- REDUCE history increments only on SELL within the current open campaign.

Artifact scan:

- Closed-campaign ADD/REDUCE leak candidates found: `0`.
- Direct PC member fields exposing cross-campaign add/reduce history leak: `0`.

Judgment:

- `CROSS_CAMPAIGN_ADD_HISTORY_LEAK_PROVEN = NO`
- `CROSS_CAMPAIGN_REDUCE_HISTORY_LEAK_PROVEN = NO`

ADD/REDUCE current-campaign history is a valid current-campaign control, not a long-lived security-level penalty, based on current evidence.

## Unknown / Missing History Fail-Closed Audit

Unknown-context REENTRY rows:

- Total unknown-context rows: `2102`
- Average age: `163.2` business days
- Median age: `126`
- P90 age: `370`
- Max age: `560`

Age distribution:

| bucket | unknown-context rows |
|---|---:|
| `<=10` | 304 |
| `11-30` | 246 |
| `31-60` | 205 |
| `61-120` | 269 |
| `121-250` | 456 |
| `251-400` | 452 |
| `>400` | 170 |

Representative late-run pattern:

- Symbol `69930` appears around `2024-12-06` through `2024-12-23` with age about `549-560` business days since prior EXIT.
- Quality/rank evidence remains relatively strong in the inspected rows, including quality around `0.75-0.773` and rank around `5-8`.
- Rows include positive/current quality evidence such as `buy_quality_full_allocation_eligible`, but still carry `reentry_unknown_prior_context_independence_not_established`.

Judgment:

Unknown prior context can create a long-lived block because the blocker is not time bounded. Current evidence can only release if it satisfies the strong-independence path; otherwise, missing prior provenance remains a REVIEW_REQUIRED reason even hundreds of business days later.

This is the cleanest repair candidate before design.

## Comparable Pair Audit

Strict never-held-vs-old-exit pairing could not be fully proven from PC artifacts because the PC population is already relationship/materialization filtered and does not consistently expose a never-held identity field for all non-REENTRY comparators. Therefore, the strongest direct evidence is classified as same-day, similar-quality `old prior-exit REENTRY` rows versus non-REENTRY comparable PC rows, not a complete never-held proof.

Twenty representative comparable rows:

| date | old-exit symbol | age | q/rank | old-exit blocker | comparator | q/rank | comparator state | classification |
|---|---:|---:|---|---|---:|---|---|---|
| 2023-04-04 | 76470 | 121 | 0.615 / 25 | unknown prior context | 78780 | 0.601 / 27 | no REENTRY blocker | old-exit asymmetry |
| 2023-04-05 | 76470 | 122 | 0.577 / 26 | unknown prior context | 45980 | 0.591 / 25 | no REENTRY blocker | old-exit asymmetry |
| 2023-04-10 | 76470 | 125 | 0.635 / 19 | unknown prior context | 41660 | 0.633 / 17 | no REENTRY blocker | old-exit asymmetry |
| 2023-04-12 | 76470 | 127 | 0.717 / 14 | unknown prior context | 27210 | 0.706 / 15 | no REENTRY blocker | old-exit asymmetry |
| 2023-04-14 | 76470 | 129 | 0.724 / 13 | unknown prior context | 51890 | 0.729 / 11 | no REENTRY blocker | old-exit asymmetry |
| 2023-04-19 | 76470 | 132 | 0.745 / 8 | unknown prior context | 77190 | 0.750 / 7 | entry allowed | old-exit asymmetry |
| 2023-04-26 | 76470 | 137 | 0.777 / 4 | unknown prior context | 77190 | 0.764 / 5 | BUY_WAIT/full quality | old-exit-specific blocker |
| 2023-04-27 | 76470 | 138 | 0.786 / 3 | unknown prior context | 77190 | 0.770 / 4 | BUY_WAIT/full quality | old-exit-specific blocker |
| 2023-04-28 | 76470 | 139 | 0.794 / 2 | unknown prior context | 77190 | 0.768 / 4 | BUY_WAIT/full quality | old-exit-specific blocker |
| 2023-05-01 | 48330 | 147 | similar-high | trend recovery not satisfied | non-REENTRY peer | similar | no REENTRY blocker | current-evidence dependent |
| 2023-05-08 | 92540 | 150+ | similar | trend recovery not satisfied | non-REENTRY peer | similar | no REENTRY blocker | current-evidence dependent |
| 2023-05-11 | 89180 | 160+ | similar | trend recovery not satisfied | non-REENTRY peer | similar | no REENTRY blocker | current-evidence dependent |
| 2024-07-01 | 89180 | 453 | high-quality cohort | trend recovery not satisfied | non-REENTRY peer | similar | no REENTRY blocker | old-exit asymmetry |
| 2024-07-01 | 69270 | 308 | high-quality cohort | unknown prior context | non-REENTRY peer | similar | no REENTRY blocker | old-exit asymmetry |
| 2024-07-02 | 77760 | 358 | high-quality cohort | hard-stop new thesis not sufficient | non-REENTRY peer | similar | no REENTRY blocker | old-exit-specific stricter hurdle |
| 2024-07-03 | 67400 | 312 | high-quality cohort | unknown prior context | non-REENTRY peer | similar | no REENTRY blocker | old-exit asymmetry |
| 2024-07-03 | 58200 | 438 | high-quality cohort | trend recovery not satisfied | non-REENTRY peer | similar | no REENTRY blocker | current-evidence dependent |
| 2024-07-04 | 69930 | 438 | high-quality cohort | unknown prior context | non-REENTRY peer | similar | no REENTRY blocker | old-exit asymmetry |
| 2024-12-06 | 69930 | 549 | 0.75+ / top-10 | unknown prior context | same-day non-REENTRY candidate | comparable | no REENTRY blocker | long-lived old-exit penalty |
| 2024-12-20 | 67400 | 434 | top cohort | unknown/trend prior context | same-day non-REENTRY candidate | comparable | no REENTRY blocker | long-lived old-exit penalty |

Conclusion:

- Strict `never-held` proof: `INSUFFICIENT_EVIDENCE` from PC artifact shape alone.
- Old-prior-exit vs non-REENTRY asymmetry: proven.
- The asymmetry is not always a defect; trend recovery and hard-stop new-thesis gates can be valid current-evidence dependencies.
- Unknown prior context beyond 400BD is the clearest effective permanent/security-level penalty candidate.

## Run-Age Accumulation

| run-age period | unique ever-held symbols | BQ-positive rows | capitalized candidates | target-zero rows | REENTRY suppression / BQ-positive | relationship suppression / BQ-positive | capitalized / BQ-positive |
|---|---:|---:|---:|---:|---:|---:|---:|
| Early 1-180 | 166 | 7452 | 2419 | 7285 | 23.1% | n/a | 32.5% |
| Mid 181-360 | 257 | 7527 | 2465 | 7214 | 34.4% | n/a | 32.7% |
| Late 361-end | 280 | 8046 | 1683 | 8171 | 45.7% | n/a | 20.9% |
| 2023 Mar-Jun | 155.3 avg | 42.0/day | 13.1/day | n/a | 27.3% | 15.7% | 31.3% |
| 2024 Jul-Dec | 471.5 avg | 42.9/day | 9.1/day | n/a | 45.6% | 7.8% | 21.3% |

Correlation evidence from EQ remains relevant:

- run age vs REENTRY suppression: `0.710`
- prior-exit symbols vs REENTRY suppression: `0.719`
- campaigns vs REENTRY suppression: `0.712`
- closed campaigns vs REENTRY suppression: `0.716`
- run age vs relationship suppression: `-0.693`

Judgment:

REENTRY suppression is run-age/history-accumulation dependent. Relationship suppression is not increasing with run age in the inspected evidence. The history accumulation effect is therefore concentrated in REENTRY/prior-exit machinery, not broad relationship or current ADD machinery.

## Runtime Slowdown Relationship

EQ already established strong runtime growth with accumulated history:

| age bucket | average seconds/day |
|---|---:|
| 1-100 | 106.63 |
| 101-200 | 147.03 |
| 201-300 | 195.43 |
| 301-400 | 233.75 |
| 401-500 | 260.81 |
| 501-end | 284.42 |

The source path shares the same unbounded-history shape:

- latest prior campaign snapshot discovery scans prior daily directories.
- prior closed campaigns are reconstructed from strict-prior executions.
- prior PM EXIT decision evidence scans prior PM artifacts.
- campaign materialization grows with accumulated executions/campaigns.

Judgment:

Runtime slowdown and REENTRY capital suppression likely share a common historical-state accumulation substrate, but only REENTRY suppression is a correctness/semantic candidate. Runtime slowdown is also a performance-scaling defect candidate.

## Defect Classification

| finding | classification |
|---|---|
| short cooldown after EXIT | `VALID_SHORT_TERM_CHURN_PROTECTION` |
| current trend/momentum recovery requirement after technical EXIT | `VALID_CURRENT_EVIDENCE_DEPENDENCY` when current PIT evidence is actually weak |
| hard-stop new thesis recovery | `LONG_LIVED_BUT_RELEASABLE_HISTORY_EFFECT` |
| old EXIT reason still gating after hundreds of business days | `LONG_LIVED_BUT_RELEASABLE_HISTORY_EFFECT`; defect candidate when relevance is not bounded |
| unknown prior context beyond 400BD | `UNKNOWN_CONTEXT_LONG_LIVED_PENALTY` and `EFFECTIVE_PERMANENT_SECURITY_LEVEL_PENALTY` candidate |
| repeated unresolved churn beyond near-term period | `POSSIBLE_EFFECTIVE_PERMANENT_PENALTY` |
| ADD count >=5 in current open campaign | `VALID_CURRENT_CAMPAIGN_HISTORY` |
| reduce count >0 in current open campaign | `VALID_CURRENT_CAMPAIGN_HISTORY` |
| closed-campaign ADD/REDUCE leakage | `NOT_A_DEFECT`; not proven |
| symbol-level ever-held/prior-exit accumulation | `WHOLE_RUN_ACCUMULATION_BIAS` |
| broad relationship suppression outside REENTRY | `NOT_A_DEFECT` in current evidence |

## Repair Candidates Before Design

These are repair-target candidates only. No repair design, threshold, expiry day, or parameter value is proposed in ER.

1. Long-lived unknown prior EXIT context causing REENTRY REVIEW_REQUIRED/target-zero even when current PIT evidence is strong.
2. Unbounded prior EXIT relevance for old symbol-level closed campaigns.
3. Repeated unresolved churn state that can persist long after the original churn context.
4. EXIT-reason-dependent recovery gates where old market/regime/profit-retention context may be treated as current security-specific thesis failure.
5. Symbol-level prior ownership classification lacking a bounded relevance/new-equivalent lifecycle.
6. Unbounded strict-prior campaign/ledger/PM artifact scans that produce both semantic accumulation and runtime slowdown.

## Required Answers

- `EFFECTIVE_PERMANENT_REENTRY_PENALTY_PROVEN = YES`
- `EFFECTIVE_PERMANENT_REENTRY_CONDITIONS = [prior closed campaign exists at symbol scope, current opportunity is routed as REENTRY/old-exit relationship, prior EXIT context is UNKNOWN or recoverable-but-not-materialized, no age-only release exists, current evidence does not satisfy the strong independence/recovery gate, PC maps REENTRY non-PASS to target zero]`
- `UNKNOWN_CONTEXT_CAN_CAUSE_LONG_LIVED_BLOCK = YES`
- `OLD_EXIT_REASON_CAN_CAUSE_LONG_LIVED_BLOCK = YES`
- `NEVER_HELD_VS_OLD_EXIT_ASYMMETRY_PROVEN = YES` for old-exit vs non-REENTRY comparable rows; strict never-held identity proof is limited by artifact fields.
- `CROSS_CAMPAIGN_ADD_HISTORY_LEAK_PROVEN = NO`
- `CROSS_CAMPAIGN_REDUCE_HISTORY_LEAK_PROVEN = NO`
- `OTHER_SECURITY_LEVEL_HISTORY_BIASES_FOUND = YES`
- `WHOLE_RUN_HISTORY_ACCUMULATION_BIAS_BEYOND_REENTRY = YES` for campaign/materialization/runtime scaling; no separate non-REENTRY capital gate was proven.
- `ALL_LONG_LIVED_HISTORY_GATES_ENUMERATED = YES` within inspected Production paths.
- `DESIGN_PHASE_READY = YES`
- `PRODUCTION_CHANGED = NO`
- `SHADOW_CHANGED = NO`
- `TARGET_RUN_MUTATED = NO`
- `RUNTIME_STATE_MUTATED = NO`
- `FUTURE_OUTCOME_USED_FOR_PRODUCTION_JUDGMENT = NO`

## Final Judgment

`PHASE32_ER_LONG_LIVED_UNKNOWN_PRIOR_EXIT_AND_UNBOUNDED_REENTRY_HISTORY_PENALTY_PROVEN_DESIGN_PHASE_READY_NO_PRODUCTION_CHANGE`
