# Phase32-P -- Post-L Early Actual-Path Semantic Verification

## Executive Summary

This was a read-only audit of the Post-L fresh Historical run through 2022-10-27:

```text
runtime-test-historical-extended-smoke-20260827T005331941551Z
```

No production code, config, threshold, model, PM, PC, MCC, Risk Pacing, PS, Runtime, state mutation, fresh-run, resume, replay, or backtest was performed.

Primary result: Phase32-L's strict-prior PM reason bridge is present and invoked in the Post-L actual path, but the expected 83060 semantic repair is not observed in the actual fresh-run PC artifacts through 2022-10-27. The bridge finds prior PM reason evidence, but every strict executed-close match count is zero. For 83060, the PM decision and daily execution artifacts carry the detailed reason and decision identity on 2022-10-04, but `.runtime/persistent_ledger/executions.jsonl`, which the L bridge reads, does not preserve `source_decision_id` or `position_campaign_id`. Therefore the prior-exit bridge falls back to bare execution action:

```text
prior_exit_reason = EXIT
previous_exit_reason_class = GENERIC
prior_exit_reason_authority = absent / fallback
```

This is not a performance failure and not a holdings/equity judgment. It is an actual-path semantic materialization/wiring failure at the persistent-ledger identity boundary.

## Run Identity

| Role | Run id | Local availability |
| --- | --- | --- |
| Pre-L comparison | `runtime-test-historical-extended-smoke-20260825T235520054579Z` | not present under `reports/runtime_tests/runs/` during this audit |
| Post-L current | `runtime-test-historical-extended-smoke-20260827T005331941551Z` | present; `run_state.json` status `RUNNING`, created `2026-08-27T00:54:55.217624Z` |

Because the Pre-L artifact directory is not locally available, direct field-by-field Pre-L artifact reads could not be repeated. The comparison below uses the user-provided Pre-L condition as baseline and verifies the Post-L actual artifacts directly.

## 83060 Lifecycle Comparison

Observed Post-L lifecycle through 2022-10-27:

| Date | Lifecycle / PC state |
| --- | --- |
| 2022-10-03 | 83060 appears as `BUY_NEW`, selected in PC; accepted weight present; BUY/fill path contains 83060 |
| 2022-10-04 | PM emits `EXIT` with detailed reason `trend_and_opportunity_broken`; execution fills SELL 83060 |
| 2022-10-05 to 2022-10-07 | 83060 appears as REENTRY candidate, blocked by cooldown plus insufficient prior context |
| 2022-10-11 to 2022-10-26 | cooldown passes, but 83060 remains `REENTRY_INSUFFICIENT_EVIDENCE` with `insufficient_prior_exit_context` |
| 2022-10-27 | 83060 remains REENTRY, but immediate blocker shifts to current buy-quality requalification: `reentry_buy_quality_not_requalified` / `BUY_WAIT` |

## Prior-Exit Field Delta

Expected Phase32-L positive actual-path shape:

```text
prior_exit_reason_authority = STRICT_PRIOR_PM_DECISION_EVIDENCE
prior_exit_reason = trend_and_opportunity_broken
previous_exit_reason_class != GENERIC
```

Observed Post-L 83060 PC fields:

| Date range | prior exit date | prior reason | authority | class | semantic | recovery / blocking state |
| --- | --- | --- | --- | --- | --- | --- |
| 2022-10-03 | empty | `UNKNOWN` | absent | `GENERIC` | `BUY_NEW` | not re-entry |
| 2022-10-04 | empty | `UNKNOWN` | absent | `TREND_MOMENTUM` on same-day exit member only | `NOT_APPLICABLE` | same-day exit, not prior re-entry |
| 2022-10-05 to 2022-10-07 | 2022-10-04 | `EXIT` | absent | `GENERIC` | `REENTRY` | cooldown `FAIL_CLOSED`; `insufficient_prior_exit_context` |
| 2022-10-11 to 2022-10-26 | 2022-10-04 | `EXIT` | absent | `GENERIC` | `REENTRY` | cooldown `PASS`; `REENTRY_INSUFFICIENT_EVIDENCE`; `insufficient_prior_exit_context` |
| 2022-10-27 | 2022-10-04 | `EXIT` | absent | `GENERIC` | `REENTRY` | `REENTRY_NOT_ELIGIBLE_CURRENT_EVIDENCE`; `reentry_buy_quality_not_requalified` |

The same-day 2022-10-04 `TREND_MOMENTUM` class is not the Phase32-L prior-exit materialization success condition. The success condition requires later re-entry artifacts to carry strict prior PM reason evidence from the earlier executed close.

## Re-Entry Gate Comparison

Condensed 83060 gate sequence:

| Date | Rank | Admission | target weight | requested | accepted | competitor status | zero reason / blocker | final PC outcome |
| --- | ---: | --- | ---: | ---: | ---: | --- | --- | --- |
| 2022-10-03 | 20 | `BUY_NEW_REDUCED_ONLY` | 0.0648 | 0.0648 | 0.0648 | `COMPETITOR_SELECTED` | none | Cash optionality residual |
| 2022-10-05 | 10 | `BUY_NEW_REDUCED_ONLY` | 0 | 0 | 0 | `COMPETITOR_REJECTED_RECONSIDERABLE` | `reentry_minimum_cooldown_not_satisfied` | Cash optionality |
| 2022-10-11 | 9 | `BUY_NEW_REDUCED_ONLY` | 0 | 0 | 0 | `COMPETITOR_REJECTED_RECONSIDERABLE` | `insufficient_prior_exit_context` | Cash optionality |
| 2022-10-19 | 7 | `BUY_NEW_REDUCED_ONLY` | 0 | 0 | 0 | `COMPETITOR_REJECTED_RECONSIDERABLE` | `insufficient_prior_exit_context` | Cash optionality |
| 2022-10-20 | 8 | `BUY_NEW_REDUCED_ONLY` | 0 | 0 | 0 | `COMPETITOR_REJECTED_RECONSIDERABLE` | `insufficient_prior_exit_context` | NEW winner 69930 |
| 2022-10-21 | 9 | `BUY_NEW_REDUCED_ONLY` | 0 | 0 | 0 | `COMPETITOR_REJECTED_RECONSIDERABLE` | `insufficient_prior_exit_context` | NEW winner 53040 |
| 2022-10-25 | 10 | `BUY_NEW_REDUCED_ONLY` | 0 | 0 | 0 | `COMPETITOR_REJECTED_RECONSIDERABLE` | `insufficient_prior_exit_context` | NEW winner 69730 |
| 2022-10-27 | 10 | `BUY_WAIT` | 0 | n/a | n/a | no NEW competitor row selected for 83060 | `buy_quality_wait` / `reentry_buy_quality_not_requalified` | Cash optionality |

If trading outcome remains unchanged, the primary semantic blocker is not rank, Cash, lot, or PC competition. It is the missing prior-exit semantic materialization through 2022-10-26:

```text
previous_exit_reason_class = GENERIC
reentry_recovery_status = REVIEW_REQUIRED
reentry_recovery_reason = insufficient_prior_exit_context
target_weight_zero_reason = insufficient_prior_exit_context
```

On 2022-10-27 specifically, the blocker becomes current evidence / buy quality:

```text
entry_admission_action = BUY_WAIT
reentry_recovery_status = FAIL_CLOSED
reentry_recovery_reason = reentry_buy_quality_not_requalified
target_weight_zero_reason = buy_quality_wait
```

## Actual-Path Lineage Verification

Phase32-L intended lineage:

```text
PM detailed EXIT reason
-> executed close with matching source decision identity
-> strict prior PM reason bridge
-> prior_exit_reason / codes / authority materialized
-> PC previous_exit_reason_class non-GENERIC
-> re-entry semantic gate can evaluate detailed context
```

Observed 83060 lineage:

| Boundary | Observed evidence | Result |
| --- | --- | --- |
| PM evidence producer | `daily/2022-10-04/position_management/pm_decisions.json` has `pm_decision_id = pm-2022-10-04-83060-exit`, `position_campaign_id = pc-37f3e1e990212b6a-83060-0001`, `decision_reason = trend_and_opportunity_broken`, `reason_codes = [trend_and_opportunity_broken]` | PASS |
| Daily execution artifact | `daily/2022-10-04/execution/fills.json` and `realized_slices.json` have `source_decision_id = pm-2022-10-04-83060-exit`, `source_decision_type = EXIT`, same campaign id | PASS |
| Prior-exit bridge invoked | `strategy/input_manifest.json` contains `phase32_l_prior_exit_state_materialization_evidence.v1` | PASS |
| PM artifact lookup | evidence counts rise from 5 on 2022-10-05 to 50 on 2022-10-27 | PASS |
| Join identity | evidence contract says `execution.source_decision_id == pm.pm_decision_id/decision_id with symbol/date/campaign validation` | expected |
| Persistent ledger source | bridge reads `.runtime/persistent_ledger/executions.jsonl`; for 83060 2022-10-04 SELL row has no `source_decision_id`, no `source_pm_decision_id`, and no `position_campaign_id` | FAIL |
| Strict match count | `pm_exit_reason_matched_close_count = 0` on every audited day | FAIL |
| Artifact materialization | PC rows carry `prior_exit_reason = EXIT`, `previous_exit_reason_class = GENERIC`, no strict authority | FAIL |

Daily prior-exit bridge counters:

| Date | prior closed campaigns | PM reason evidence | matched closes | supplied symbols |
| --- | ---: | ---: | ---: | ---: |
| 2022-10-05 | 3 | 5 | 0 | 2 |
| 2022-10-11 | 6 | 11 | 0 | 5 |
| 2022-10-18 | 16 | 26 | 0 | 11 |
| 2022-10-21 | 19 | 31 | 0 | 10 |
| 2022-10-27 | 28 | 50 | 0 | 14 |

The problem is not that the PM evidence cannot be found. It is found. The problem is that the persistent ledger execution rows no longer expose the exact execution-to-PM decision identity required by the strict bridge.

## Early Additional Symbol Sample

Across 2022-10-03 through 2022-10-27:

```text
PC members with prior exit history = 136
semantic REENTRY rows = 136
symbols with semantic REENTRY rows = 22
PC members with previous_exit_reason_class != GENERIC = 0
PC members with prior_exit_reason_authority = STRICT_PRIOR_PM_DECISION_EVIDENCE = 0
```

Sample affected symbols:

```text
83060, 89180, 41650, 33700, 44220, 93600, 45750, 73590, 76470, 59860,
17570, 33580, 48330, 65500, 66190, 66330, 73560, 79220, 91070, 92540,
96100
```

This confirms 83060 is not the only early re-entry row failing to receive non-GENERIC strict prior context in PC artifacts.

## Trading Outcome

No PnL, equity, return, or holdings acceptance judgment was made.

83060 does not re-enter by 2022-10-27. That is not by itself a failure. The semantic failure is that the intended detailed prior-exit context never reaches the later re-entry PC rows. Through 2022-10-26, the operative field-level blocker remains:

```text
target_weight = 0
requested_weight = 0
accepted_weight = 0
competitor_status = COMPETITOR_REJECTED_RECONSIDERABLE
target_weight_zero_reason = insufficient_prior_exit_context
```

On 2022-10-27, current buy-quality requalification also blocks the row:

```text
entry_admission_action = BUY_WAIT
target_weight_zero_reason = buy_quality_wait
```

## Defect / No-Defect Judgment

Judgment: actual-path repair not confirmed; likely wiring/materialization defect.

Evidence:

- Phase32-L implementation and regression tests expect matching PM decision id, symbol, date, and campaign to materialize `STRICT_PRIOR_PM_DECISION_EVIDENCE`.
- Post-L actual artifacts produce the Phase32-L evidence object.
- PM evidence exists and is counted.
- Daily execution artifacts preserve source decision identity.
- Persistent ledger rows consumed by the bridge do not preserve `source_decision_id` / `position_campaign_id`.
- Match count is zero across the audited period.
- PC re-entry artifacts remain `EXIT` / `GENERIC`.

This is narrower than "Phase32-L code absent." The actual-path bridge is present, but the source ledger it uses has already lost the identity needed for the bridge to work.

## Recommendation

The current 650BD run should not be treated as validating Phase32-L re-entry semantics. It may continue only as a non-acceptance exploratory run, but for Phase32-L acceptance it should not continue as the authoritative validation path until the persistent-ledger identity gap is understood and repaired.

Recommended next step:

```text
READ-ONLY root-cause audit of execution ledger append/normalization:
daily fills/realized_slices preserve source_decision_id and campaign id,
but .runtime/persistent_ledger/executions.jsonl drops them before
_supply_prior_exit_state reads the ledger.
```

After that, perform a narrow repair only if confirmed, then restart a fresh validation run from 2022-10-03. Do not change re-entry thresholds, Cash, PC competition, Risk Pacing, ADD/NEW priority, or Runtime semantics based on this audit.

## Final Judgments

```text
PHASE32_P_POST_L_PM_REASON_ACTUAL_PATH_OBSERVED = YES

PHASE32_P_POST_L_NON_GENERIC_PRIOR_EXIT_OBSERVED = NO

PHASE32_P_83060_PRIOR_EXIT_REASON_CHANGED = NO

PHASE32_P_83060_PREVIOUS_EXIT_CLASS_CHANGED = NO

PHASE32_P_REENTRY_SEMANTIC_CHANGED = NO

PHASE32_P_TRADING_OUTCOME_CHANGED_BY_2022_10_27 = NO

PHASE32_P_IF_SAME_OUTCOME_PRIMARY_BLOCKER = PERSISTENT_LEDGER_DROPS_SOURCE_DECISION_ID_AND_CAMPAIGN_ID_SO_STRICT_PRIOR_PM_REASON_MATCH_COUNT_REMAINS_ZERO; 83060_FIELD_BLOCKER_THROUGH_2022_10_26 = insufficient_prior_exit_context; 2022_10_27_ADDITIONAL_BLOCKER = buy_quality_wait / reentry_buy_quality_not_requalified

PHASE32_P_PHASE32_L_ACTUAL_PATH_REPAIR_CONFIRMED = NO

PHASE32_P_PHASE32_L_REGRESSION_OR_WIRING_DEFECT = YES

PHASE32_P_CURRENT_650BD_RUN_CONTINUE = NO

PHASE32_P_NEXT_STEP = READ_ONLY_EXECUTION_LEDGER_IDENTITY_PRESERVATION_AUDIT_THEN_NARROW_REPAIR_IF_CONFIRMED_BEFORE_RESTARTING_FRESH_VALIDATION
```
